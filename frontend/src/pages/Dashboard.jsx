import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api/api.js'
import Sidebar from '../components/Sidebar.jsx'
import FileUpload from '../components/FileUpload.jsx'
import DocumentList from '../components/DocumentList.jsx'

export default function Dashboard() {
  const [docs, setDocs] = useState([])

  const load = useCallback(() => {
    api.get('/docs/list').then((r) => setDocs(r.data))
  }, [])

  useEffect(load, [load])

  return (
    <div className="flex">
      <Sidebar />
      <main className="h-screen flex-1 space-y-6 overflow-y-auto p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">Your documents</h1>
          {docs.length > 0 && (
            <Link to="/chat" className="rounded-lg bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700">
              Chat with documents
            </Link>
          )}
        </div>
        <FileUpload onUploaded={load} />
        <DocumentList docs={docs} onChanged={load} />
      </main>
    </div>
  )
}
