import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setJpegQuality(95);
Config.setChromiumOpenGlRenderer('angle');
Config.setOverwriteOutput(true);
Config.setEntryPoint('src/index.ts');
