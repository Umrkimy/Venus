import { DEMO, DEMO_PROJECT_IDS } from "@/features/demo/demo-mode";
import ProjectPage from "./project-page";

// Same as chat/[id]: the static demo builds its project pages up front.
export function generateStaticParams() {
  return DEMO ? DEMO_PROJECT_IDS.map((id) => ({ id })) : [];
}

export default function Page() {
  return <ProjectPage />;
}
