Add a new test case to the evaluation set.

Steps:
1. Ask the user for the description (what someone would type to find a word) and the expected word.
   - If the user already provided these in the command, use them directly.
2. Classify the difficulty:
   - easy: description is a synonym or close paraphrase of the definition
   - medium: description is in the user's own words but clearly points to one word
   - hard: description is evocative, poetic, or indirect
3. If the system is running, run the query right now and check whether the expected word appears in the top 10. Report the rank if found, or "not found" if not.
4. Confirm the test case with the user before writing it:
   ```
   Description: "<description>"
   Expected word: "<word>"
   Difficulty: <easy|medium|hard>
   Currently ranks: <rank or "not found">
   Add this test case? (yes/no)
   ```
5. On confirmation, append to `eval/test_cases.jsonl`:
   ```json
   {"description": "<description>", "expected_word": "<word>", "difficulty": "<easy|medium|hard>"}
   ```
6. Report the new total test case count.
7. If the word was "not found" in step 3, note: "This is a failing case — it will count against recall@10 until fixed. That's intentional."
