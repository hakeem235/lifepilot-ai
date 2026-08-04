# LifePilot AI — Mobile (Expo / React Native)

## Running the app

This app **cannot run in Expo Go** — Expo Go 57's Hermes runtime SIGSEGVs on
launch for this project (reproduced down to a bare hello-world on clean
emulators). Use a native dev build instead:

```bash
npm run android   # expo run:android
npm run ios       # expo run:ios  (requires Xcode)
```

## Android build requirement — JDK 21

React Native's CMake configure tasks fail on JDK 25 (the JDK bundled with
current Android Studio):

```
restricted method in java.lang.System has been called → configureCMakeDebug FAILED
```

The Gradle daemon JVM must be **JDK 21 (LTS)**. Set `LIFEPILOT_ANDROID_JAVA_HOME`
to your JDK 21 path before prebuild/build and the `withAndroidJdkHome` config
plugin (see `plugins/`) will pin `org.gradle.java.home` durably — it re-applies
on every `expo prebuild`, unlike a manual edit to the gitignored
`android/gradle.properties`.

```bash
export LIFEPILOT_ANDROID_JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
npm run android
```

If your default `java` is already JDK 21, leave the variable unset — the plugin
is a no-op and Gradle uses your default JVM.
