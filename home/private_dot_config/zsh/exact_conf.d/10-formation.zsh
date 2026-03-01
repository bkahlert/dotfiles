# GCloud credentials for formation/DKB (IntelliJ environment only)
if [ "${INTELLIJ_ENVIRONMENT_READER-}" ]; then
  credentials="$HOME/.gcloud/mvn-access.json"
  if [ -f "$credentials" ]; then
    export GOOGLE_APPLICATION_CREDENTIALS="$credentials"
  fi
fi
