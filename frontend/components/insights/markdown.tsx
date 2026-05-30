"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import remarkGfm from "remark-gfm";

/**
 * 安全的 Markdown 渲染器。
 * - remark-gfm：表格/删除线/任务列表
 * - rehype-sanitize：白名单净化，杜绝脚本/危险 HTML（防存储型 XSS）
 * - 站内 /stocks/{id} 等相对链接用 next/link 跳转；外链新窗口打开
 */

// 在默认白名单基础上允许 <details>/<summary>（日报数据明细折叠用）
const schema = {
  ...defaultSchema,
  tagNames: [...(defaultSchema.tagNames || []), "details", "summary"],
};

export function Markdown({ content }: { content: string }) {
  return (
    <div className="md-body max-w-none text-body leading-relaxed text-primary">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, schema]]}
        components={{
          h1: ({ children }) => <h1 className="mb-3 mt-2 text-display text-primary">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 mt-5 text-title font-medium text-primary">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1.5 mt-4 text-body font-medium text-secondary">{children}</h3>,
          p: ({ children }) => <p className="my-2 text-secondary">{children}</p>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5 text-secondary">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5 text-secondary">{children}</ol>,
          li: ({ children }) => <li className="text-secondary">{children}</li>,
          strong: ({ children }) => <strong className="font-medium text-primary">{children}</strong>,
          blockquote: ({ children }) => (
            <blockquote className="my-3 border-l-2 border-border-strong bg-elevated/40 px-3 py-1.5 text-tertiary">
              {children}
            </blockquote>
          ),
          code: ({ children }) => (
            <code className="rounded bg-elevated px-1.5 py-0.5 text-caption text-primary">{children}</code>
          ),
          hr: () => <hr className="my-4 border-border-default" />,
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto">
              <table className="w-full border-collapse text-small">{children}</table>
            </div>
          ),
          th: ({ children }) => (
            <th className="border border-border-default bg-elevated px-3 py-1.5 text-left text-caption text-secondary">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border border-border-default px-3 py-1.5 text-secondary">{children}</td>
          ),
          a: ({ href, children }) => {
            const url = href || "";
            if (url.startsWith("/")) {
              return (
                <Link href={url} className="text-accent underline underline-offset-2 hover:opacity-80">
                  {children}
                </Link>
              );
            }
            return (
              <a
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent underline underline-offset-2 hover:opacity-80"
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
