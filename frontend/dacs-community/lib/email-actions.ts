export function emailError(error: any) {
  const code=String(error?.code || '');
  if (code.includes('expired-action-code')) return 'This link has expired. Return to the community and request a new email.';
  if (code.includes('invalid-action-code')) return 'This link has already been used or is invalid. Return to the community to check your account or request a new email.';
  if (code.includes('unauthorized-continue-uri') || code.includes('invalid-continue-uri')) return 'The return address is not approved in Firebase Authentication. Contact the Secretariat.';
  if (code.includes('too-many-requests') || code.includes('quota-exceeded')) return 'Email requests are temporarily limited. Please try again later.';
  if (code.includes('network-request-failed')) return 'Connection interrupted. Check your internet connection and try again.';
  return error?.message || 'The email action could not be completed. Please try again.';
}
