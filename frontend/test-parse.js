const out = "user,admin\naso,false";
function parseCSV(text) {
  const result = []
  let row = []
  let inQuotes = false
  let curVal = ''
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    const next = text[i+1]
    if (inQuotes) {
      if (c === '\\') {
        if (next === '"') { curVal += '"'; i++; } else { inQuotes = false }
      } else { curVal += c }
    } else {
      if (c === '"') { inQuotes = true }
      else if (c === ',') { row.push(curVal); curVal = '' }
      else if (c === '\n' || c === '\r') {
        row.push(curVal); curVal = ''
        if (row.length > 0 && !(row.length === 1 && row[0] === '')) { result.push(row) }
        row = []
        if (c === '\r' && next === '\n') { i++ }
      } else { curVal += c }
    }
  }
  if (curVal || row.length > 0) {
    row.push(curVal)
    if (row.length > 0 && !(row.length === 1 && row[0] === '')) { result.push(row) }
  }
  return result
}
console.log("PARSED:", JSON.stringify(parseCSV(out)));
