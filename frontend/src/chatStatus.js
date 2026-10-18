const reasons = {
  AUTHENTICATION_FAILED: 'Autenticazione del provider AI non riuscita.',
  ACCESS_DENIED: 'Accesso al modello non consentito dal provider.',
  MODEL_NOT_FOUND: 'Modello non disponibile per questa configurazione.',
  RATE_LIMITED: 'Limite di richieste o quota del provider raggiunto.',
  INVALID_REQUEST: 'Il provider ha rifiutato la richiesta al modello.',
  MODEL_PROVIDER_MISMATCH: 'Modello e provider configurati non compatibili.',
  MISSING_CONFIGURATION: 'Configurazione AI incompleta.',
  UNSUPPORTED_PROVIDER: 'Provider AI non supportato.',
  TIMEOUT: 'Il provider AI non ha risposto in tempo.',
  EMPTY_RESPONSE: 'Il modello ha restituito una risposta vuota.',
  MODEL_UNAVAILABLE: 'Provider AI temporaneamente non disponibile.',
};
export function formatChatAnswer(result) {
  const detail = result.fallback_reason ? (reasons[result.fallback_reason] || 'Motivo non disponibile.') : '';
  return `${result.answer}\n\nMotore: ${result.provider}${result.fallback ? ` · risposta di riserva${detail ? `\n${detail}` : ''}` : ''}`;
}
