import { Routes, Route } from "react-router";
import { ThemeProvider } from "./components/ThemeProvider";
import { Layout } from "./components/Layout";
import { LandingPage } from "./components/LandingPage";
import { DocsHome } from "./components/docs/DocsHome";
import { QuickstartPage } from "./components/docs/QuickstartPage";
import { ConfigurationPage } from "./components/docs/ConfigurationPage";
import { ApiReferencePage } from "./components/docs/ApiReferencePage";
import { IntegrationsHome } from "./components/integrations/IntegrationsHome";
import { IntegrationPage } from "./components/integrations/IntegrationPage";
import { AsciiViewer } from "./components/AsciiViewer";

function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/docs" element={<DocsHome />} />
          <Route path="/docs/quickstart" element={<QuickstartPage />} />
          <Route path="/docs/configuration" element={<ConfigurationPage />} />
          <Route path="/docs/api" element={<ApiReferencePage />} />
          <Route path="/integrations" element={<IntegrationsHome />} />
          <Route path="/integrations/:platform" element={<IntegrationPage />} />
        </Route>
        <Route path="/ascii-viewer" element={<AsciiViewer />} />
      </Routes>
    </ThemeProvider>
  );
}

export default App;