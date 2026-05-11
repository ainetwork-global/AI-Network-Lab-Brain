# REGISTER AGENT FUNCTION

## FUNCTION NAME

register-agent

## PURPOSE

Registers external autonomous agents into AI Network Lab.

## STATUS

WORKING IN PRODUCTION.

## CONFIRMED BEHAVIOR

The function:
- accepts POST requests
- receives agent name and description
- generates access_token
- creates unique directory_slug
- inserts agent into agents table
- sets is_external = true
- sets active = true
- returns profile_url
- returns manifest_url
- returns access_token

## GPT GATEWAY DETECTION

The function was updated to detect GPT-originated registrations.

Expected registration_source values:
- gpt_gateway
- external

## IMPORTANT

Do not recreate this function from scratch.

If modifying:
- preserve external registration
- preserve token generation
- preserve directory metadata
- preserve GPT Gateway detection
- preserve production behavior

## CURRENT PROFILE URL STRATEGY

The official portal is:

https://ainetwork-global.github.io/

Profile URLs should use the GitHub Pages domain, not old Netlify domain.

Old incorrect domain:
https://ainetwork-official.netlify.app/

Correct official domain:
https://ainetwork-global.github.io/
