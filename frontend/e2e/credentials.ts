export function deploymentPassword(account: 'admin' | 'analyst' | 'student'): string {
  const key = `NETRUNNER_${account.toUpperCase()}_PASSWORD`;
  const value = process.env[key];
  if (!value) throw new Error(`${key} is missing; run ./start.sh init`);
  return value;
}

export function isServerDeployment(): boolean {
  return (process.env.NETRUNNER_DEPLOYMENT_MODE || 'server').toLowerCase() === 'server';
}
