import { parseCSV } from './src/composables/useDatabaseConfig.ts';
const out = "user,admin\naso,false";
console.log(JSON.stringify(parseCSV(out)));
