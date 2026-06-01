import { useEffect } from "react";

import { usePathname } from "./lib/navigation";
import { LandingPage } from "./pages/LandingPage";
import { WorkbenchApp } from "./pages/WorkbenchApp";

function isWorkbenchPath(pathname: string) {
  return pathname === "/workbench" || pathname.startsWith("/workbench/");
}

export function App() {
  const { pathname, navigate } = usePathname();
  const showWorkbench = isWorkbenchPath(pathname);

  useEffect(() => {
    document.body.classList.toggle("landing-mode", !showWorkbench);
    document.body.classList.toggle("workbench-mode", showWorkbench);
  }, [showWorkbench]);

  if (showWorkbench) {
    return <WorkbenchApp onGoHome={() => navigate("/")} />;
  }

  return <LandingPage onOpenWorkbench={() => navigate("/workbench")} />;
}
