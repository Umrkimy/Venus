"use client";

import { useParams } from "next/navigation";

import ProjectView from "@/features/projects/project-view";

export default function ProjectPage() {
  const { id } = useParams<{ id: string }>();
  // key: opening another project starts a fresh page instead of reusing state.
  return <ProjectView key={id} projectId={id} />;
}
