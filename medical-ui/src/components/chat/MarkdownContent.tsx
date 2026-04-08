import ReactMarkdown from 'react-markdown';

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className = '' }: MarkdownContentProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
          li: ({ children }) => <li className="text-sm leading-relaxed">{children}</li>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
          code: ({ children, className }) => {
            const isInline = !className;
            return isInline ? (
              <code className="px-1.5 py-0.5 rounded bg-white/10 text-primary-300 text-xs font-mono">
                {children}
              </code>
            ) : (
              <code className="block p-3 rounded-lg bg-black/30 text-gray-300 text-xs font-mono overflow-x-auto my-2">
                {children}
              </code>
            );
          },
          h3: ({ children }) => <h3 className="font-semibold text-gray-200 mt-3 mb-1">{children}</h3>,
          h4: ({ children }) => <h4 className="font-medium text-gray-300 mt-2 mb-1">{children}</h4>,
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-primary-500/40 pl-3 my-2 text-gray-400 italic">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
