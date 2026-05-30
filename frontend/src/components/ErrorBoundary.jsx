import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('ErrorBoundary caught:', error, info)
  }

  handleReset = () => this.setState({ hasError: false, error: null })

  render() {
    if (this.state.hasError) {
      return (
        <div className="container">
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Something went wrong.</h2>
            <p className="muted">{this.state.error?.message || 'Unexpected error.'}</p>
            <button className="primary" onClick={this.handleReset}>Try again</button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
