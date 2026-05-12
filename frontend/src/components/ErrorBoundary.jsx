import React, { Component } from "react"

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-3xl border border-red-100 bg-red-50 p-6 text-red-900 shadow-sm">
          <p className="text-lg font-semibold">Something went wrong.</p>
          <p className="mt-2 text-sm leading-6">{this.state.error.message}</p>
          <button
            className="mt-4 rounded-full border border-red-200 bg-white px-4 py-2 text-sm font-semibold text-red-800"
            onClick={() => this.setState({ error: null })}
            type="button"
          >
            Try Again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
