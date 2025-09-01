import { HistoryIcon, CheckCircle2, BarChart3 } from "lucide-react"
import { NavLink } from "react-router-dom"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import bhLogo from "@/assets/bh-logo.png"

const menuItems = [
  {
    title: "Historique des conversations",
    url: "/historique",
    icon: HistoryIcon,
  },
  {
    title: "Validation des réponses",
    url: "/validation",
    icon: CheckCircle2,
  },
  {
    title: "Analyse de Performance",
    url: "/analytics",
    icon: BarChart3,
  },
]

export function DashboardSidebar() {
  const { state } = useSidebar()
  const isCollapsed = state === "collapsed"

  return (
    <Sidebar className={isCollapsed ? "w-20" : "w-80"} collapsible="icon">
      <SidebarContent className="bg-bh-navy">
        {/* Logo Header */}
        <div className="flex items-center justify-center p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img 
              src={bhLogo} 
              alt="BH Assurance" 
              className={`transition-all duration-300 ${isCollapsed ? "h-8" : "h-10"}`}
            />
            {!isCollapsed && (
              <div className="text-white">
                <h2 className="font-bold text-lg">Dashboard</h2>
                <p className="text-white/70 text-sm">Administration</p>
              </div>
            )}
          </div>
        </div>

        <SidebarGroup>
          <SidebarGroupLabel className="text-white/80 font-medium">
            {!isCollapsed && "Gestion IA"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {menuItems.map((item) => (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton asChild className="text-white hover:bg-white/10 hover:text-white">
                    <NavLink 
                      to={item.url} 
                      className={({ isActive }) =>
                        `flex items-center gap-3 p-3 rounded-lg transition-colors ${
                          isActive ? "bg-bh-red text-white font-medium" : ""
                        }`
                      }
                    >
                      <item.icon className="h-5 w-5" />
                      {!isCollapsed && <span className="text-sm">{item.title}</span>}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  )
}