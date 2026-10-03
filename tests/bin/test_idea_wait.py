class TestIdeaWait:
    def test_should_run_idea_with_the_arguments_followed_by_wait(self, run, fake_bin, calls):
        fake_bin("idea", exit_code=7)
        result = run("idea-wait", "-n", "COMMIT_EDITMSG")
        assert result.returncode == 7
        assert calls("idea") == [["-n", "COMMIT_EDITMSG", "--wait"]]
