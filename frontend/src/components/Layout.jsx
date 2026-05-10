import TopNav from "./TopNav.jsx"

export default function Layout({ tabs, activeTab, onTabChange, children }) {
  return (
    <div className="min-h-screen bg-background text-neutral-950">
      <TopNav tabs={tabs} activeTab={activeTab} onTabChange={onTabChange} />
      <main className="mx-auto max-w-[1180px] px-6 py-10">{children}</main>
    </div>
  )
}
