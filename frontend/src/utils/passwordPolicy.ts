export interface PasswordRuleResult {
  id: "minLength" | "hasUppercase" | "hasLowercase" | "hasDigit" | "hasSpecial"
  label: string
  passed: boolean
}

export function checkPasswordPolicy(password: string): PasswordRuleResult[] {
  return [
    {
      id: "minLength",
      label: "Tối thiểu 8 ký tự",
      passed: password.length >= 8,
    },
    {
      id: "hasUppercase",
      label: "Có chữ cái in hoa (A–Z)",
      passed: /[A-Z]/.test(password),
    },
    {
      id: "hasLowercase",
      label: "Có chữ cái thường (a–z)",
      passed: /[a-z]/.test(password),
    },
    {
      id: "hasDigit",
      label: "Có chữ số (0–9)",
      passed: /[0-9]/.test(password),
    },
    {
      id: "hasSpecial",
      label: "Có ký tự đặc biệt (!@#$%...)",
      passed: /[^A-Za-z0-9\s]/.test(password),
    },
  ]
}

export function isStrongPassword(password: string): boolean {
  return checkPasswordPolicy(password).every((r) => r.passed)
}

export function getFirstPasswordError(password: string): string | null {
  const failed = checkPasswordPolicy(password).find((r) => !r.passed)
  if (!failed) return null
  return `Mật khẩu chưa đạt yêu cầu: ${failed.label.toLowerCase()}.`
}
