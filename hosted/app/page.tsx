import { KernelApp } from "@/components/kernel-app";
import { createExampleMemory } from "@/lib/example-memory";
export default function Home() { return <KernelApp example={createExampleMemory()} />; }
