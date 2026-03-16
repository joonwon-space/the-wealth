"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { BarChart3, Home, LogOut, Moon, Sun, Wallet } from "lucide-react";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "대시보드", icon: Home },
  { href: "/dashboard/portfolios", label: "포트폴리오", icon: Wallet },
  { href: "/dashboard/analytics", label: "분석", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <aside className="flex h-screen w-60 flex-col border-r bg-sidebar px-3 py-4">
      <div className="mb-6 px-2">
        <span className="text-xl font-bold tracking-tight">THE WEALTH</span>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
              pathname === href
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent/60"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>

      <div className="flex flex-col gap-1 border-t pt-3">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors"
        >
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {theme === "dark" ? "라이트 모드" : "다크 모드"}
        </button>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent/60 transition-colors"
        >
          <LogOut className="h-4 w-4" />
          로그아웃
        </button>
      </div>
    </aside>
  );
}
