"""Milestone 4 media ingestion, FFprobe metadata extraction, thumbnailing, and proxying test suite."""

import shutil
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.errors import AppError
from app.core.storage import StorageLayout
from app.db.migrator import run_migrations
from app.main import create_app
from app.services.jobs import JobOrchestrator
from app.services.media import MediaService
from app.services.media_pipeline import MediaPipelineService
from app.services.media_probe import probe_media_file
from app.services.media_proxy import generate_proxy
from app.services.media_thumbnail import generate_thumbnail
from app.services.projects import ProjectService


@pytest.fixture
def media_env(tmp_path: Path):
    """Set up isolated storage, database, and synthetic test media files."""
    storage_root = tmp_path / "storage"
    layout = StorageLayout.from_root(storage_root)
    layout.ensure_directories()

    settings = Settings(
        storage_root=storage_root,
        environment="testing",
        log_level="DEBUG",
        ffmpeg_threads=2,
    )

    run_migrations(
        db_path=layout.db_file,
        migrations_dir=settings.migrations_dir,
        backup_dir=layout.backups,
    )

    # Generate synthetic test media using FFmpeg
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None, "FFmpeg must be installed and on PATH for Milestone 4 tests."

    sample_dir = tmp_path / "samples"
    sample_dir.mkdir(parents=True, exist_ok=True)

    # 1. Synthetic test video: 2.0s, 1280x720, 30fps, test tone audio
    video_path = sample_dir / "test_synth_video.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-f", "lavfi", "-i", "testsrc=duration=2:size=1280x720:rate=30",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "64k",
            str(video_path),
            "-y",
        ],
        capture_output=True,
        check=True,
    )

    # 2. Synthetic test audio: 2.0s sine wave WAV
    audio_path = sample_dir / "test_synth_audio.wav"
    subprocess.run(
        [
            ffmpeg,
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "pcm_s16le",
            str(audio_path),
            "-y",
        ],
        capture_output=True,
        check=True,
    )

    # 3. Synthetic test image: 640x480 solid color JPEG
    image_path = sample_dir / "test_synth_image.jpg"
    subprocess.run(
        [
            ffmpeg,
            "-f", "lavfi", "-i", "color=c=blue:size=640x480:duration=1",
            "-vframes", "1",
            str(image_path),
            "-y",
        ],
        capture_output=True,
        check=True,
    )

    # 4. Corrupt file
    corrupt_path = sample_dir / "corrupt_data.mp4"
    corrupt_path.write_bytes(b"NOT_A_VALID_MP4_HEADER_GARBAGE_BYTES_1234567890")

    return {
        "settings": settings,
        "storage": layout,
        "tmp_path": tmp_path,
        "video": video_path,
        "audio": audio_path,
        "image": image_path,
        "corrupt": corrupt_path,
    }


def test_real_ffprobe_extraction(media_env):
    """Verify FFprobe extracts correct container, codecs, dimensions, and audio streams."""
    # Test video probe
    v_probe = probe_media_file(media_env["video"])
    assert v_probe.media_type == "video"
    assert v_probe.width == 1280
    assert v_probe.height == 720
    assert v_probe.aspect_ratio == "16:9"
    assert v_probe.video_codec == "h264"
    assert v_probe.audio_codec == "aac"
    assert v_probe.duration_seconds is not None and v_probe.duration_seconds >= 1.8
    assert v_probe.file_size_bytes > 0
    assert len(v_probe.streams) >= 2

    # Test audio probe
    a_probe = probe_media_file(media_env["audio"])
    assert a_probe.media_type == "audio"
    assert a_probe.audio_codec in {"pcm_s16le", "pcm_s16be", "wav"}
    assert a_probe.sample_rate == 44100
    assert a_probe.channels == 1

    # Test image probe
    i_probe = probe_media_file(media_env["image"])
    assert i_probe.media_type == "image"
    assert i_probe.width == 640
    assert i_probe.height == 480
    assert i_probe.video_codec in {"mjpeg", "jpeg"}

    # Test corrupt file probe fails gracefully
    with pytest.raises(AppError) as exc_info:
        probe_media_file(media_env["corrupt"])
    assert exc_info.value.code == "CORRUPT_MEDIA"


def test_real_thumbnail_generation(media_env):
    """Verify thumbnail generator creates valid JPEG thumbnails for video and image."""
    thumb_video_out = media_env["tmp_path"] / "thumb_video.jpg"
    res_v = generate_thumbnail(
        source_path=media_env["video"],
        output_path=thumb_video_out,
        media_type="video",
        duration=2.0,
    )
    assert res_v is not None
    assert thumb_video_out.exists()
    assert thumb_video_out.stat().st_size > 0

    # Probe generated thumbnail to verify it's a valid JPEG
    t_probe = probe_media_file(thumb_video_out)
    assert t_probe.media_type == "image"
    assert t_probe.width == 640

    # Image thumbnail
    thumb_img_out = media_env["tmp_path"] / "thumb_img.jpg"
    res_i = generate_thumbnail(
        source_path=media_env["image"],
        output_path=thumb_img_out,
        media_type="image",
    )
    assert res_i is not None
    assert thumb_img_out.exists()


def test_real_proxy_generation(media_env):
    """Verify proxy transcode generates lightweight downscaled 480p and 360p MP4 files."""
    proxy_480p_out = media_env["tmp_path"] / "proxy_480p.mp4"
    res = generate_proxy(
        source_path=media_env["video"],
        output_path=proxy_480p_out,
        profile="480p",
        max_threads=2,
    )
    assert res.exists()
    assert res.stat().st_size > 0

    # Probe proxy to verify resolution and codecs
    p_probe = probe_media_file(proxy_480p_out)
    assert p_probe.media_type == "video"
    assert p_probe.width <= 854
    assert p_probe.video_codec == "h264"
    assert p_probe.audio_codec == "aac"
    assert p_probe.duration_seconds is not None and p_probe.duration_seconds >= 1.8


def test_media_pipeline_local_import_modes(media_env):
    """Verify local import supports both external referencing and storage copying."""
    settings = media_env["settings"]
    layout = media_env["storage"]
    ms = MediaService(settings=settings, db_path=layout.db_file)
    ps = ProjectService(settings=settings, db_path=layout.db_file)
    jobs = JobOrchestrator(settings=settings, db_path=layout.db_file)
    pipeline = MediaPipelineService(settings, layout, ms, ps, jobs)

    proj = ps.create_project("Media Test Project", "Testing pipeline modes")

    # 1. External Reference Mode (copy_to_storage=False)
    ref_asset = pipeline.import_local_media(
        project_id=proj.id,
        file_path=str(media_env["video"]),
        copy_to_storage=False,
        generate_proxy_now=False,
        generate_thumbnail_now=True,
    )
    assert ref_asset.is_external is True
    assert ref_asset.storage_path == str(media_env["video"].resolve())
    assert ref_asset.thumbnail_reference_path is not None
    assert Path(ref_asset.thumbnail_reference_path).exists()
    assert ref_asset.duration_seconds is not None

    # Verify background job was recorded
    import_jobs = jobs.list_jobs(project_id=proj.id, status="completed")
    assert len(import_jobs) >= 1
    assert import_jobs[0].job_type == "media_import"

    # 2. Managed Storage Mode (copy_to_storage=True)
    copy_asset = pipeline.import_local_media(
        project_id=proj.id,
        file_path=str(media_env["audio"]),
        copy_to_storage=True,
        generate_proxy_now=False,
        generate_thumbnail_now=True,
    )
    assert copy_asset.is_external is False
    assert copy_asset.storage_path != str(media_env["audio"].resolve())
    assert Path(copy_asset.storage_path).exists()
    assert media_env["audio"].exists()  # Source file preserved intact!


def test_media_pipeline_proxy_lifecycle_and_delete(media_env):
    """Verify proxy generation, stats calculation, and safe asset deletion."""
    settings = media_env["settings"]
    layout = media_env["storage"]
    ms = MediaService(settings=settings, db_path=layout.db_file)
    ps = ProjectService(settings=settings, db_path=layout.db_file)
    jobs = JobOrchestrator(settings=settings, db_path=layout.db_file)
    pipeline = MediaPipelineService(settings, layout, ms, ps, jobs)

    proj = ps.create_project("Proxy Lifecycle Project")

    # Import video with copy to storage
    asset = pipeline.import_local_media(
        project_id=proj.id,
        file_path=str(media_env["video"]),
        copy_to_storage=True,
        generate_proxy_now=False,
        generate_thumbnail_now=True,
    )
    assert asset.proxy_status == "none"

    # Trigger proxy generation
    asset_with_proxy = pipeline.generate_proxy_for_asset(proj.id, asset.id, profile="360p")
    assert asset_with_proxy.proxy_status == "ready"
    assert asset_with_proxy.proxy_reference_path is not None
    proxy_file = Path(asset_with_proxy.proxy_reference_path)
    assert proxy_file.exists()

    # Verify stats
    stats = pipeline.get_project_media_stats(proj.id)
    assert stats.total_media_count == 1
    assert stats.total_proxy_bytes > 0
    assert stats.total_thumbnail_bytes > 0
    assert stats.managed_files_count == 1

    # Safe deletion
    thumb_file = Path(asset_with_proxy.thumbnail_reference_path)
    source_file = Path(asset_with_proxy.storage_path)

    pipeline.delete_media_asset(proj.id, asset.id, delete_source_file=True)

    assert not proxy_file.exists()
    assert not thumb_file.exists()
    assert not source_file.exists()
    assert len(ms.list_media_assets(proj.id)) == 0


def test_media_http_api_endpoints(media_env):
    """Test REST API media endpoints via TestClient."""
    app = create_app(settings_override=media_env["settings"])
    with TestClient(app) as client:
        # Create Project
        p_res = client.post("/api/v1/projects", json={"name": "HTTP Media Project"})
        assert p_res.status_code == 201
        pid = p_res.json()["id"]

        # 1. Local import endpoint
        imp_res = client.post(
            f"/api/v1/projects/{pid}/media/import-local",
            json={
                "file_path": str(media_env["video"]),
                "copy_to_storage": False,
                "generate_proxy": False,
                "generate_thumbnail": True,
            },
        )
        assert imp_res.status_code == 201
        asset = imp_res.json()
        assert asset["original_filename"] == "test_synth_video.mp4"
        assert asset["duration_seconds"] is not None
        aid = asset["id"]

        # 2. Thumbnail serving endpoint
        t_res = client.get(f"/api/v1/projects/{pid}/media/{aid}/thumbnail")
        assert t_res.status_code == 200
        assert t_res.headers["content-type"] == "image/jpeg"
        assert len(t_res.content) > 0

        # 3. Proxy generation endpoint
        pr_res = client.post(
            f"/api/v1/projects/{pid}/media/{aid}/proxy",
            json={"profile": "480p"},
        )
        assert pr_res.status_code == 200
        assert pr_res.json()["proxy_status"] == "ready"

        # 4. Proxy file serving endpoint
        pf_res = client.get(f"/api/v1/projects/{pid}/media/{aid}/proxy")
        assert pf_res.status_code == 200
        assert pf_res.headers["content-type"] == "video/mp4"

        # 5. Storage stats endpoint
        s_res = client.get(f"/api/v1/projects/{pid}/media/storage-stats")
        assert s_res.status_code == 200
        assert s_res.json()["total_media_count"] == 1
        assert s_res.json()["total_proxy_bytes"] > 0

        # 6. Upload endpoint
        with open(media_env["audio"], "rb") as faudio:
            up_res = client.post(
                f"/api/v1/projects/{pid}/media/upload",
                files={"file": ("uploaded_audio.wav", faudio, "audio/wav")},
            )
            assert up_res.status_code == 201
            assert up_res.json()["media_type"] == "audio"

        # 7. List media with filters
        list_all = client.get(f"/api/v1/projects/{pid}/media")
        assert list_all.status_code == 200
        assert list_all.json()["total"] == 2

        list_videos = client.get(f"/api/v1/projects/{pid}/media?media_type=video")
        assert list_videos.status_code == 200
        assert list_videos.json()["total"] == 1

        list_audio = client.get(f"/api/v1/projects/{pid}/media?media_type=audio")
        assert list_audio.status_code == 200
        assert list_audio.json()["total"] == 1
