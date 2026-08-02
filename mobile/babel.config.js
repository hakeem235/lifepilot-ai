module.exports = function (api) {
  api.cache(true);
  return {
    presets: [
      // worklets: false — nativewind/babel already injects the worklets plugin;
      // letting babel-preset-expo add its own copy double-instruments worklets
      // and SIGSEGVs Hermes at runtime (crashed Expo Go, Issue 8.1 app run).
      ["babel-preset-expo", { jsxImportSource: "nativewind", worklets: false }],
      "nativewind/babel",
    ],
  };
};
