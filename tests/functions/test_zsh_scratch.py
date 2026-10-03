TARGET = ".config/zsh/conf.d/90-scratch.zsh"


class TestZshScratch:
    def test_should_open_the_source_in_the_editor_and_apply_the_target(self, zsh, fake_bin, calls, sandbox):
        fake_bin("chezmoi", script='[[ $1 == source-path ]] && echo /src/90-scratch.zsh\nexit 0\n')
        fake_bin("editor")
        sandbox.env["EDITOR"] = "editor"
        result = zsh("zsh-scratch", function="zsh-scratch")
        assert result.returncode == 0
        assert calls("editor") == [["/src/90-scratch.zsh"]]
        assert calls("chezmoi") == [["source-path", f"{sandbox.home}/{TARGET}"],
                                    ["apply", f"{sandbox.home}/{TARGET}"]]

    class TestOnUnmanagedTarget:
        def test_should_return_1_without_opening_the_editor(self, zsh, fake_bin, calls, sandbox):
            fake_bin("chezmoi", exit_code=1)
            fake_bin("editor")
            sandbox.env["EDITOR"] = "editor"
            result = zsh("zsh-scratch", function="zsh-scratch")
            assert result.returncode == 1
            assert calls("editor") == []
