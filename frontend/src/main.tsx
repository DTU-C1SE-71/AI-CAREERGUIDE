import { GoogleOAuthProvider } from "@react-oauth/google"
import React from "react"
import ReactDOM from "react-dom/client"
import App from "./App"
import { AssessmentProvider } from "./context/AssessmentContext"
import { AuthProvider } from "./context/AuthContext"
import "./index.css"

const GOOGLE_CLIENT_ID =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  "1095956825384-f8n2bj0ott0u1sokbegksf7n32tlpn51.apps.googleusercontent.com"

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <AuthProvider>
        <AssessmentProvider>
          <App />
        </AssessmentProvider>
      </AuthProvider>
    </GoogleOAuthProvider>
  </React.StrictMode>,
)
