import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import TeacherApp from "./teacher/TeacherApp";
import "./styles.css";

// One page, two surfaces. Branching on the path gives /teacher a real, shareable URL
// without pulling in a router for what is currently two screens. Vite's dev server
// serves index.html for unknown paths, so this works without extra config.
const isTeacher = window.location.pathname.startsWith("/teacher");

createRoot(document.getElementById("root")!).render(
  <StrictMode>{isTeacher ? <TeacherApp /> : <App />}</StrictMode>
);
