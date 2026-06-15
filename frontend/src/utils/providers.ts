export function formatProviderName(provider: string | null | undefined): string {
  if (!provider) {
    return "n/a";
  }
  if (provider === "mistral") {
    return "Mistral";
  }
  if (provider === "ollama") {
    return "Ollama";
  }
  if (provider === "mock") {
    return "Mock";
  }
  return provider.charAt(0).toUpperCase() + provider.slice(1);
}
