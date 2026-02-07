# Architecture Drift Postmortem (Brain Stem)

## What happened
- Framework mirror-system docs were mixed into the Brain Stem project repo.

## Fix
- Removed framework-phase doc from phases/ and reserved phases/ for project-only docs.
- Introduced explicit repo boundaries + multi-project protocol.

## Prevention
- Operator gate: classify every doc as FRAMEWORK vs PROJECT before export/push.
- Framework governance lives in: https://github.com/sharedterrain/mirror-framework
