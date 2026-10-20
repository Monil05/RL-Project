import { Component, type ReactNode } from "react";
import { ErrorText } from "./ui";

interface State {
  message: string | null;
}

export class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { message: null };

  static getDerivedStateFromError(error: Error): State {
    return { message: error.message };
  }

  render() {
    if (this.state.message) {
      return (
        <div className="p-8">
          <ErrorText>This page failed to render: {this.state.message}</ErrorText>
        </div>
      );
    }
    return this.props.children;
  }
}
