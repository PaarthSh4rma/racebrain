import LandingPage from "./components/product/LandingPage";
import NotFoundPage from "./components/product/NotFoundPage";
import SimulationLabPage from "./components/simulation/SimulationLabPage";
import WorkbenchPage from "./components/workbench/WorkbenchPage";

function routePath() {
  const normalized = window.location.pathname.replace(/\/+$/, "");
  return normalized || "/";
}

export default function App() {
  switch (routePath()) {
    case "/":
      return <LandingPage />;
    case "/workbench":
      return <WorkbenchPage />;
    case "/simulation":
      return <SimulationLabPage />;
    default:
      return <NotFoundPage />;
  }
}
