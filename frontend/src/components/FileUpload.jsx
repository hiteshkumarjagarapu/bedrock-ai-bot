import { useRef, useState } from 'react'
import api from '../api/api.js'

export default function FileUpload({ onUploaded }) {
  const inputRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)

  const upload = async (file) => {
    if (!file) return
    setBusy(true)
    setError('')
    const form = new FormData()
    form.append('file', file)
    try {
      await api.post('/docs/upload', form)
      onUploaded?.()
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed')
    } finally {
      setBusy(false)
      if (inputRef.current) inputRef.current.value = ''
    }
  }

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files[0]) }}
        className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center ${
          drag ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-800' : 'border-gray-300 dark:border-gray-600'
        }`}
      >
        <input ref={inputRef} type="file" accept=".pdf,.docx,.pptx" hidden onChange={(e) => upload(e.target.files[0])} />
        {busy ? 'Embedding and indexing… this can take a moment' : 'Click or drop a PDF, DOCX or PPTX (max 10MB)'}
      </div>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  )
}
