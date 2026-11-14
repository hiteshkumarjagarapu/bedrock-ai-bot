import api from '../api/api.js'

export default function DocumentList({ docs, onChanged }) {
  const remove = async (id) => {
    if (!window.confirm('Delete this document?')) return
    await api.delete(`/docs/${id}`)
    onChanged?.()
  }

  if (!docs.length) return <p className="text-gray-500">No documents yet.</p>

  return (
    <ul className="divide-y divide-gray-200 rounded-lg border border-gray-200 bg-white dark:divide-gray-700 dark:border-gray-700 dark:bg-gray-800">
      {docs.map((d) => (
        <li key={d.id} className="flex items-center justify-between p-3">
          <div>
            <div className="font-medium">{d.filename}</div>
            <div className="text-xs text-gray-500">
              {d.file_type.toUpperCase()} · {d.chunk_count} chunks · {new Date(d.created_at + 'Z').toLocaleString()}
            </div>
          </div>
          <button onClick={() => remove(d.id)} className="text-sm text-red-500 hover:underline">Delete</button>
        </li>
      ))}
    </ul>
  )
}
