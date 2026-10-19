# merq-sherlock image

Build from the root of this repository:

```bash
docker build -f image/Dockerfile -t merq-sherlock:<git-sha> .
```

Push an immutable tag to `898546818973.dkr.ecr.us-east-1.amazonaws.com/merq-sherlock:<git-sha>`.

The image contains the Sherlock runner, prompts, and reviewed playbooks. It does not contain MerQube application checkouts. Those stay in their own repositories and should be cloned at pinned SHAs during CI when a case needs local code.

Do not pass real credentials as `docker build` arguments. Runtime credentials come from the `sherlock-secrets` Kubernetes Secret.
