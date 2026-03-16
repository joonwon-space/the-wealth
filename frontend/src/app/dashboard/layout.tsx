"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { KeyboardShortcutsDialog } from "@/components/KeyboardShortcutsDialog";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [searchOpen, setSearchOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((prev) => !prev);
      }
      // Cmd+? (Cmd+Shift+/)
      if ((e.metaKey || e.ctrlKey) && e.shiftKey && e.key === "/") {
        e.preventDefault();
        setShortcutsOpen((prev) => !prev);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-4 md:p-6">{children}</main>
      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={() => setSearchOpen(false)}
      />
      <KeyboardShortcutsDialog
        open={shortcutsOpen}
        onClose={() => setShortcutsOpen(false)}
      />
    </div>
  );
}
