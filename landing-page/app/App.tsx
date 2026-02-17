import { Navigation } from "./components/Navigation";
import { Hero } from "./components/Hero";
import { BentoGrid } from "./components/BentoGrid";
import { Architecture } from "./components/Architecture";
import { CodeExample } from "./components/CodeExample";
import { Installation } from "./components/Installation";
import { CTA } from "./components/CTA";
import { Footer } from "./components/Footer";
import { ThemeProvider } from "./components/ThemeProvider";

function App() {
  return (
    <ThemeProvider>
      <div className="min-h-screen antialiased" style={{ backgroundColor: "var(--bg-primary)", color: "var(--text-primary)" }}>
        <Navigation />
        <Hero />
        <BentoGrid />
        <Architecture />
        <CodeExample />
        <Installation />
        <CTA />
        <Footer />
      </div>
    </ThemeProvider>
  );
}

export default App;