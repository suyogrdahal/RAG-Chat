# AWS Infrastructure Scaffolding (CloudFormation)

This folder contains split CloudFormation stacks for a free-tier-conscious AWS deployment of this monorepo.

## Stacks

- `network.yaml`: Creates VPC, 2 public subnets, 2 private subnets, IGW, and route tables. Exports subnet and VPC IDs for other stacks.
- `database.yaml`: Creates PostgreSQL RDS (Single-AZ, private), DB subnet group, and DB security group. Imports network exports.
- `app.yaml`: Creates EC2 instance, IAM role/profile, app security group, and optional Elastic IP. Installs Nginx, Python, Node.js, and CodeDeploy agent via UserData.
- `cicd.yaml`: Creates S3 artifact bucket, CodeBuild, CodeDeploy app/deployment group, and CodePipeline using CodeCommit -> CodeBuild -> CodeDeploy.

## Deployment Order

1. `network`
2. `database`
3. `app`
4. `cicd`

## Example Deploy Commands

Run from repo root.

```bash
aws cloudformation deploy \
  --stack-name ragchat-network \
  --template-file infra/network.yaml \
  --capabilities CAPABILITY_NAMED_IAM
```

```bash
aws cloudformation deploy \
  --stack-name ragchat-database \
  --template-file infra/database.yaml \
  --parameter-overrides \
    NetworkStackName=ragchat-network \
    DBName=ragchat \
    DBUser=ragchat_admin \
    DBPassword='CHANGE_ME_NOW' \
    DBAllocatedStorage=20 \
    DBInstanceClass=db.t3.micro \
  --capabilities CAPABILITY_NAMED_IAM
```

```bash
aws cloudformation deploy \
  --stack-name ragchat-app \
  --template-file infra/app.yaml \
  --parameter-overrides \
    NetworkStackName=ragchat-network \
    InstanceType=t3.micro \
    AdminCidr=YOUR.PUBLIC.IP/32 \
    DeploymentTagKey=DeployGroup \
    DeploymentTagValue=ragchat-app \
    AssociateElasticIp=true \
  --capabilities CAPABILITY_NAMED_IAM
```

```bash
aws cloudformation deploy \
  --stack-name ragchat-cicd \
  --template-file infra/cicd.yaml \
  --parameter-overrides \
    RepositoryName=ragchat-repo \
    BranchName=main \
    ExistingCodeCommitRepo=false \
    DeploymentTagKey=DeployGroup \
    DeploymentTagValue=ragchat-app \
  --capabilities CAPABILITY_NAMED_IAM
```

## Parameters You Must Customize

- `AdminCidr` in `app.yaml` deployment command (do not keep `0.0.0.0/0`).
- `DBPassword` in `database.yaml` deployment command.
- `RepositoryName`, `BranchName` in `cicd.yaml`.
- `DeploymentTagKey` / `DeploymentTagValue` must match between app and cicd stacks.
- Optional: `KeyPairName` in app stack if SSH key access is required.

## CodeCommit Push Flow

Get repository clone URL from CI/CD stack output `RepositoryCloneUrlHttp`.

```bash
git remote add aws https://git-codecommit.<region>.amazonaws.com/v1/repos/ragchat-repo
git push aws main
```

For HTTPS auth, configure `git-remote-codecommit` or AWS credential helper.

## Delivery Flow

1. Commit and push to CodeCommit branch.
2. CodePipeline `Source` stage pulls the commit.
3. CodeBuild runs `buildspec.yml` and packages deployment artifact.
4. CodeDeploy deploys artifact to tagged EC2 instance.
5. CodeDeploy runs hooks in `appspec.yml`:
   - `ApplicationStop` -> `deploy/scripts/stop.sh`
   - `BeforeInstall` -> `deploy/scripts/install.sh`
   - `ApplicationStart` -> `deploy/scripts/start.sh`

## Troubleshooting

- CodeDeploy failures on EC2:
  - Ensure `codedeploy-agent` is running on instance.
  - Verify EC2 has IAM instance profile and outbound internet access via public subnet + IGW.
- Pipeline source errors:
  - Confirm repository exists if `ExistingCodeCommitRepo=true`.
  - Confirm branch name exists.
- Build failures:
  - Verify `frontend/package-lock.json` exists for `npm ci`.
  - Verify Node/Python versions in `buildspec.yml` are supported by your CodeBuild image.
- App not reachable:
  - Confirm security group allows port 80.
  - Check `nginx -t`, `systemctl status nginx fastapi nextjs` on EC2.
- DB connectivity issues:
  - Use RDS endpoint output from database stack in `/opt/app/shared/.env`.
  - Confirm backend connects to private RDS host over VPC networking.
