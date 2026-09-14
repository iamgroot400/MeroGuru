import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { GoalProvider } from "./context";
import "@fontsource-variable/dm-sans";
import "@fontsource-variable/manrope";
import "./styles.css";

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <main className="fatal">
        <h1>This page could not be opened.</h1>
        <p>Try reloading your learning space.</p>
        <button onClick={() => window.location.reload()}>
          Reload MeroGuru
        </button>
      </main>
    ) : (
      this.props.children
    );
  }
}
ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <GoalProvider>
          <App />
        </GoalProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>,
);
