# WeChat share signer

This service generates WeChat JS-SDK signatures for HTTPS pages on
`qinzy.tech`. It runs on a small EC2 instance with a fixed Elastic IP so the
source address can be added to the WeChat Official Account IP whitelist.

## AWS deployment

- AWS profile: `qinzy.cs@gmail.com`
- Region: `ap-southeast-1`
- AppID: `wxbd83f6ed93c8184e`
- AppSecret parameter: `/qinzy/wechat/app-secret` (`SecureString`)
- Elastic IP / WeChat whitelist IP: `54.251.121.171`
- EC2 instance: `i-00cc8fecfe9f90a7f` (`t4g.nano`)
- CloudFront distribution: `E17WTKAAC3XOI5`
- Public HTTPS: `https://d3dp3fxu4p4bho.cloudfront.net`
- Origin access: restricted to the AWS-managed CloudFront origin prefix list

The AppSecret must never be committed to this repository. Store it directly
from a local terminal:

```sh
read -s "WECHAT_SECRET?WeChat AppSecret: "
aws --profile 'qinzy.cs@gmail.com' --region ap-southeast-1 ssm put-parameter \
  --name '/qinzy/wechat/app-secret' \
  --type SecureString \
  --value "$WECHAT_SECRET" \
  --overwrite
unset WECHAT_SECRET
```

Add `54.251.121.171` to the WeChat Official Account IP whitelist before
testing `/sign`.

## Domain verification

`MP_verify_maaUdVOKsPFX9ZdG.txt` is intentionally committed in this directory.
Its Jekyll permalink publishes it at
`https://www.qinzy.tech/MP_verify_maaUdVOKsPFX9ZdG.txt`, as required by WeChat,
without placing the source file at the repository root. It is a public
verification token, not a secret.
