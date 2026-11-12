import React, { useEffect, useState } from 'react';
import {
  BookOpen,
  ChevronRight,
  Clock,
  Lightbulb,
  Search,
  Tag,
} from 'lucide-react';
import {
  fetchDocArticleDetail,
  fetchDocArticles,
  fetchDocCategories,
} from '../../services/apiClient';
import { DocArticle, DocArticleDetail, DocCategory } from '../../types/system';

export const DocumentationView: React.FC = () => {
  const [categories, setCategories] = useState<DocCategory[]>([]);
  const [articles, setArticles] = useState<DocArticle[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedArticleId, setSelectedArticleId] = useState<string>('architecture-overview');
  const [articleDetail, setArticleDetail] = useState<DocArticleDetail | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const loadCategories = async () => {
      try {
        const [cats, arts] = await Promise.all([
          fetchDocCategories(),
          fetchDocArticles(),
        ]);
        setCategories(cats);
        setArticles(arts);
      } catch {
        // ignore
      }
    };
    void loadCategories();
  }, []);

  useEffect(() => {
    if (!selectedArticleId) return;
    const loadArticle = async () => {
      try {
        const detail = await fetchDocArticleDetail(selectedArticleId);
        setArticleDetail(detail);
      } catch {
        // ignore
      }
    };
    void loadArticle();
  }, [selectedArticleId]);

  const filteredArticles = articles.filter((a) => {
    if (selectedCategory !== 'all' && a.category !== selectedCategory) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      return (
        a.title.toLowerCase().includes(q) ||
        a.summary.toLowerCase().includes(q) ||
        a.tags.some((t) => t.toLowerCase().includes(q))
      );
    }
    return true;
  });

  return (
    <div className="flex-1 flex flex-col h-full bg-canvas text-text-primary overflow-hidden">
      {/* Top Header */}
      <div className="p-4 border-b border-border bg-surface/50 backdrop-blur-sm flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-indigo-400" />
            <h1 className="text-lg font-semibold tracking-tight">Studio Documentation & User Guides</h1>
          </div>
          <p className="text-xs text-text-muted mt-0.5">
            Practical user guides, architecture blueprints, and workflow references for ZezEdit 2.0.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-72">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search guides, topics, tags..."
            className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-surface border border-border text-xs text-text-primary focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Navigation Sidebar */}
        <div className="w-72 shrink-0 border-r border-border bg-surface flex flex-col h-full overflow-hidden">
          {/* Category Tabs */}
          <div className="p-3 border-b border-border space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted px-2">
              Categories
            </span>
            <div className="space-y-0.5">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                  selectedCategory === 'all'
                    ? 'bg-indigo-600/15 text-indigo-400 font-semibold'
                    : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                }`}
              >
                <span>All Guides</span>
                <span className="text-[10px] font-mono text-text-muted">{articles.length}</span>
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.id}
                  onClick={() => setSelectedCategory(cat.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition ${
                    selectedCategory === cat.id
                      ? 'bg-indigo-600/15 text-indigo-400 font-semibold'
                      : 'text-text-secondary hover:text-text-primary hover:bg-surface-hover'
                  }`}
                >
                  <span className="truncate">{cat.name}</span>
                  <span className="text-[10px] font-mono text-text-muted">{cat.article_count}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Article List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted px-2 py-1 block">
              Articles
            </span>
            {filteredArticles.map((art) => {
              const isSelected = selectedArticleId === art.id;
              return (
                <button
                  key={art.id}
                  onClick={() => setSelectedArticleId(art.id)}
                  className={`w-full text-left p-2.5 rounded-xl border transition space-y-1 ${
                    isSelected
                      ? 'bg-indigo-600/10 border-indigo-500/40 text-text-primary'
                      : 'bg-canvas/50 border-border/60 hover:border-border hover:bg-surface-hover text-text-secondary'
                  }`}
                >
                  <div className="font-medium text-xs text-text-primary line-clamp-1">{art.title}</div>
                  <div className="text-[11px] text-text-muted line-clamp-2 leading-relaxed">{art.summary}</div>
                  <div className="flex items-center gap-2 pt-1 text-[10px] text-text-muted font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>{art.reading_time_minutes}m read</span>
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Article Viewer */}
        <div className="flex-1 overflow-y-auto p-8 bg-canvas">
          {articleDetail ? (
            <div className="max-w-3xl mx-auto space-y-6">
              {/* Breadcrumb & Metadata */}
              <div className="flex items-center gap-2 text-xs text-text-muted font-mono">
                <span className="uppercase text-indigo-400">{articleDetail.category}</span>
                <ChevronRight className="w-3.5 h-3.5" />
                <span className="truncate">{articleDetail.title}</span>
              </div>

              {/* Tags */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {articleDetail.tags.map((t) => (
                  <span
                    key={t}
                    className="px-2 py-0.5 rounded-md bg-surface border border-border text-[10px] text-text-muted flex items-center gap-1"
                  >
                    <Tag className="w-2.5 h-2.5" />
                    <span>{t}</span>
                  </span>
                ))}
              </div>

              {/* Article Content Rendered */}
              <div className="prose prose-invert prose-slate max-w-none text-text-secondary text-sm leading-relaxed space-y-4">
                {articleDetail.markdown_content.split('\n\n').map((block, idx) => {
                  if (block.startsWith('# ')) {
                    return (
                      <h1 key={idx} className="text-2xl font-bold text-text-primary tracking-tight pb-2 border-b border-border">
                        {block.replace('# ', '')}
                      </h1>
                    );
                  }
                  if (block.startsWith('### ')) {
                    return (
                      <h3 key={idx} className="text-base font-semibold text-text-primary pt-3">
                        {block.replace('### ', '')}
                      </h3>
                    );
                  }
                  if (block.startsWith('- ')) {
                    const items = block.split('\n- ');
                    return (
                      <ul key={idx} className="list-disc pl-5 space-y-1 text-text-secondary">
                        {items.map((item, i) => (
                          <li key={i}>{item.replace(/^- /, '')}</li>
                        ))}
                      </ul>
                    );
                  }
                  return <p key={idx}>{block}</p>;
                })}
              </div>

              {/* Related Guides Section */}
              {articleDetail.related_article_ids.length > 0 && (
                <div className="pt-8 border-t border-border space-y-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-text-muted flex items-center gap-1.5">
                    <Lightbulb className="w-4 h-4 text-amber-400" />
                    <span>Related Documentation</span>
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    {articleDetail.related_article_ids.map((relId) => {
                      const relArt = articles.find((a) => a.id === relId);
                      if (!relArt) return null;
                      return (
                        <button
                          key={relId}
                          onClick={() => setSelectedArticleId(relId)}
                          className="p-3 rounded-xl bg-surface border border-border hover:border-indigo-500/40 text-left transition space-y-1"
                        >
                          <span className="font-semibold text-xs text-text-primary block line-clamp-1">
                            {relArt.title}
                          </span>
                          <span className="text-[11px] text-text-muted line-clamp-1 block">
                            {relArt.summary}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-16 text-center text-text-muted">Select an article to view instructions.</div>
          )}
        </div>
      </div>
    </div>
  );
};
