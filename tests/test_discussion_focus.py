import unittest
from chemtutor.discussion import is_social_or_process_only, final_contribution_turns


class DiscussionFocusTests(unittest.TestCase):
    def test_generic_promise_does_not_replace_reasoning(self):
        messages = [
            {'id': 'T1', 'role': 'student', 'text': 'I should divide by 0.7 before taking the square root to get x = 5.'},
            {'id': 'T2', 'role': 'teacher', 'text': 'That seems overly complicated.'},
            {'id': 'T3', 'role': 'student', 'text': 'Yes, I understand. I will make sure to simplify the problem as much as possible and only use the information given to me to solve the problem.'},
        ]
        self.assertEqual([t['id'] for t in final_contribution_turns(messages)], ['T1', 'T2'])

    def test_gratitude_does_not_hide_answer(self):
        messages = [
            {'id': 'T1', 'role': 'student', 'text': 'He should charge $45.'},
            {'id': 'T2', 'role': 'teacher', 'text': 'Well done!'},
            {'id': 'T3', 'role': 'student', 'text': "Thank you! I'm glad I was able to understand the problem and get the right answer."},
        ]
        self.assertEqual([t['id'] for t in final_contribution_turns(messages)], ['T1'])

    def test_explicit_replacement_does_not_revive_old_error(self):
        messages = [
            {'id': 'T1', 'role': 'student', 'text': 'It is 17 dollars.'},
            {'id': 'T2', 'role': 'student', 'text': 'Actually, it is 11 dollars because only the wallet was destroyed.'},
            {'id': 'T3', 'role': 'student', 'text': 'I will check my work next time.'},
        ]
        self.assertEqual([t['id'] for t in final_contribution_turns(messages)], ['T2'])

    def test_no_digit_math_explanation_is_not_social(self):
        for text in ['I understand that the number of houses is the number of treats.',
                     'I will divide the total by the number of children.',
                     'The square root is necessary.', '我会先减去花掉的钱再取一半。',
                     'Thank you! The answer is five boxes.']:
            with self.subTest(text=text):
                self.assertFalse(is_social_or_process_only(text))

    def test_acknowledgment_with_numeric_answer_is_substantive(self):
        self.assertFalse(is_social_or_process_only('Yes, I understand now. It is 5.'))

    def test_english_chinese_process_promises(self):
        for text in ['Yes, that makes sense. Thanks for helping me understand the problem better.', 'Great! Thanks for checking my work.', 'Yes, I understand now. I appreciate your help.',
                     'I will be more careful next time.', '谢谢，明白了，我下次会认真检查。']:
            self.assertTrue(is_social_or_process_only(text))


if __name__ == '__main__':
    unittest.main()
