// src/components/Login.tsx
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { useNavigate } from "react-router-dom"
import bhLogo from "@/assets/bh-logo.png"

export default function Login() {
  const [email, setEmail] = useState("admin@bh-assurance.tn")
  const [password, setPassword] = useState("admin123")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError("")

    try {
      const res = await fetch("http://localhost:3001/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.error || "Échec de connexion")
      }

      // Stocker le token
      localStorage.setItem("token", data.token)
      localStorage.setItem("user", JSON.stringify(data.user))

      // Rediriger
      navigate("/")
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-bh-light-blue">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <img src={bhLogo} alt="BH Assurance" className="h-16 mx-auto mb-4" />
          <CardTitle className="text-2xl">Connexion Administrateur</CardTitle>
          <CardDescription>
            Accédez à votre dashboard de gestion
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <Label htmlFor="password">Mot de passe</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Connexion..." : "Se connecter"}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-muted-foreground">
            <p>Utilisateur test :</p>
            <p><strong>Email :</strong> admin@bh-assurance.tn</p>
            <p><strong>Mot de passe :</strong> admin123</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}