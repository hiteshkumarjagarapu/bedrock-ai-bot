import ReactMarkdown from 'react-markdown'
import StreamingText from './StreamingText.jsx'

export default function MessageBubble({ message, streaming }) {
  const isUser = message.role === 'user'
  const sources = [...new Map((message.sources || []).map((s) => [`${s.filename}:${s.page_number}`, s])).values()]
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-2 ${
          isUser ? 'bg-indigo-600 text-white' : 'bg-white shadow dark:bg-gray-800'
        } ${message.error ? 'border border-red-500 text-red-500' : ''}`}
      >
        {isUser ? (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        ) : (
          <StreamingText text={message.content} streaming={streaming} />
        )}
        {!isUser && sources.length > 0 && !streaming && (
          <div className="mt-2 flex flex-wrap gap-1 border-t border-gray-200 pt-2 text-xs text-gray-500 dark:border-gray-700">
            {sources.map((s) => (
              <span key={`${s.filename}:${s.page_number}`} className="rounded bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
                {s.filename} · p.{s.page_number}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
