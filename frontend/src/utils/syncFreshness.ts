export function hasNewCompletedSync(
  previousId: number | null | undefined,
  currentId: number | null,
): boolean {
  return previousId !== undefined && currentId !== null && currentId !== previousId;
}
