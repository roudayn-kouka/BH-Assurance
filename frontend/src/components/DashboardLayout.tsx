import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { DashboardSidebar } from "./DashboardSidebar"
import { Menu } from "lucide-react"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full">
        <DashboardSidebar />
        
        <div className="flex-1 flex flex-col relative">
          {/* Header with trigger */}
          <header className="h-16 border-b bg-card flex items-center px-4 shadow-sm relative z-10">
            <SidebarTrigger className="mr-4">
              <Menu className="h-5 w-5" />
            </SidebarTrigger>
            <div className="flex items-center gap-4">
              <h1 className="text-xl font-semibold text-primary">
                Dashboard BH Assurance
              </h1>
            </div>
          </header>

          {/* Main content */}
          <main className="flex-1 overflow-auto bg-background relative z-0">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}