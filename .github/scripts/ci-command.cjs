// Resolve a request using trusted event metadata and GitHub's current permissions.
// The caller checks out this handler from the workflow revision, not PR code.
module.exports = async function resolveRequest({ github, context }) {
  const repository = `${context.repo.owner}/${context.repo.repo}`;
  if (context.eventName === 'workflow_dispatch') {
    return { repository, sha: context.sha, pr: '' };
  }

  const { action, issue, comment } = context.payload;
  if (
    context.eventName !== 'issue_comment' || action !== 'created' ||
    !issue?.pull_request ||
    !/^\/ci run(?: compatibility)?$/.test(comment?.body?.trim() ?? '')
  ) return null;

  const { data: access } = await github.rest.repos.getCollaboratorPermissionLevel({
    ...context.repo, username: comment.user.login,
  });
  if (!['write', 'maintain', 'admin'].includes(access.permission)) {
    throw new Error('Running upstream compatibility requires repository write access.');
  }

  const { data: pr } = await github.rest.pulls.get({
    ...context.repo, pull_number: issue.number,
  });
  if (pr.state !== 'open' || !pr.head.repo) {
    throw new Error('The pull request must be open with an available source repository.');
  }
  if (!/^[0-9a-f]{40}$/.test(pr.head.sha)) {
    throw new Error('GitHub did not return a valid pull request head commit.');
  }
  return { repository: pr.head.repo.full_name, sha: pr.head.sha, pr: String(issue.number) };
};
