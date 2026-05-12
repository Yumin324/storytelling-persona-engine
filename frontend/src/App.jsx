import React, { useState } from "react"

import Layout from "./components/Layout.jsx"
import PersonaBank from "./pages/PersonaBank.jsx"
import Production from "./pages/Production.jsx"
import Studio from "./pages/Studio.jsx"

const tabs = {
  personas: { label: "Persona Bank", component: PersonaBank },
  studio: { label: "Studio", component: Studio },
  production: { label: "Production", component: Production },
}

export default function App() {
  const [activeTab, setActiveTab] = useState("personas")
  const ActivePage = tabs[activeTab].component

  return (
    <Layout tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
      <ActivePage onNavigate={setActiveTab} />
    </Layout>
  )
}
