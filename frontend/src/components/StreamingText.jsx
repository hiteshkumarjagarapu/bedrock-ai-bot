import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function StreamingText({ text, streaming }) {
  return (
    <div className="markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
      {streaming && <span className="inline-block h-4 w-2 animate-pulse bg-gray-500 align-middle" />}
    </div>
  )
}
