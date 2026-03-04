import { useNavigate } from 'react-router-dom'

export default function NotFoundPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center bg-base-200">
      <div className="text-center">
        <h1 className="text-8xl font-bold text-base-content/20">404</h1>
        <h2 className="text-2xl font-semibold mt-4">Page Not Found</h2>
        <p className="text-base-content/70 mt-2 max-w-md">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <div className="mt-6 flex gap-2 justify-center">
          <button className="btn btn-primary" onClick={() => navigate('/dashboard')}>
            Go to Dashboard
          </button>
          <button className="btn btn-ghost" onClick={() => navigate(-1)}>
            Go Back
          </button>
        </div>
      </div>
    </div>
  )
}
