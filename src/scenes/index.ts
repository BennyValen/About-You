import React from 'react';
import {Grade} from '../kit/post';
import {SceneProps} from '../kit/layers';
import * as S01 from './S01NightTrain';
import * as S02 from './S02ContourForest';
import * as S03 from './S03LilyPads';
import * as S04 from './S04FrozenLake';
import * as S05 from './S05Desert';
import * as S06 from './S06Lagoon';
import * as S07 from './S07Canyon';
import * as S08 from './S08NightSwim';
import * as S09 from './S09LakePath';
import * as S10 from './S10Sunflowers';
import * as S11 from './S11Cranes';
import * as S12 from './S12TidalFlats';

export type SceneDef = {Component: React.FC<SceneProps>; grade: (f: number) => Grade};

const LIST: SceneDef[] = [S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, S11, S12];

export const SCENES: SceneDef[] = Array.from({length: 12}, (_, i) => LIST[Math.min(i, LIST.length - 1)]);
