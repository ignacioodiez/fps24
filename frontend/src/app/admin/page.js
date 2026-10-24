import TodayHeader from "@/components/TodayHeader";
import PanelAdmin from "@/components/PanelAdmin";

// Fuera del sitemap y de buscadores. Quién es admin lo decide la API (ADMIN_EMAILS); a los demás, el 404 normal.
export const metadata = { title: "Admin - FPS24", robots: { index: false, follow: false } };

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-background text-foreground pb-20">
      <TodayHeader />
      <PanelAdmin />
    </main>
  );
}
