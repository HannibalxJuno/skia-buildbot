package testutils

import (
	"fmt"
	"io/ioutil"
	"os"
	"path"
	"strings"
	"testing"
	"time"

	"github.com/satori/go.uuid"
	assert "github.com/stretchr/testify/require"
	"go.skia.org/infra/go/exec"
	"go.skia.org/infra/go/git/git_common"
	"go.skia.org/infra/go/testutils"
)

// GitBuilder creates commits and branches in a git repo.
type GitBuilder struct {
	t      *testing.T
	dir    string
	branch string
}

// GitInit creates a new git repo in a temporary directory and returns a
// GitBuilder to manage it. Call Cleanup to remove the temporary directory. The
// current branch will be master.
func GitInit(t *testing.T) *GitBuilder {
	tmp, err := ioutil.TempDir("", "")
	assert.NoError(t, err)

	g := &GitBuilder{
		t:      t,
		dir:    tmp,
		branch: "master",
	}

	g.run("git", "init")
	g.run("git", "remote", "add", "origin", ".")

	return g
}

// Cleanup removes the directory containing the git repo.
func (g *GitBuilder) Cleanup() {
	testutils.RemoveAll(g.t, g.dir)
}

// Dir returns the directory of the git repo, e.g. for cloning.
func (g *GitBuilder) Dir() string {
	return g.dir
}

// RepoUrl returns a git-friendly URL for the repo.
func (g *GitBuilder) RepoUrl() string {
	return fmt.Sprintf("file://%s", g.Dir())
}

func (g *GitBuilder) run(cmd ...string) string {
	output, err := exec.RunCwd(g.dir, cmd...)
	assert.NoError(g.t, err)
	return output
}

func (g *GitBuilder) runCommand(cmd *exec.Command) string {
	cmd.InheritEnv = true
	cmd.Dir = g.dir
	output, err := exec.RunCommand(cmd)
	assert.NoError(g.t, err)
	return output
}

func (g *GitBuilder) write(filepath, contents string) {
	fullPath := path.Join(g.dir, filepath)
	dir := path.Dir(fullPath)
	if dir != "" {
		assert.NoError(g.t, os.MkdirAll(dir, os.ModePerm))
	}
	assert.NoError(g.t, ioutil.WriteFile(fullPath, []byte(contents), os.ModePerm))
}

func (g *GitBuilder) push() {
	g.run("git", "push", "origin", g.branch)
}

// genString returns a string with arbitrary content.
func genString() string {
	return uuid.NewV1().String()
}

// Add writes contents to file and adds it to the index.
func (g *GitBuilder) Add(file, contents string) {
	g.write(file, contents)
	g.run("git", "add", file)
}

// AddGen writes arbitrary content to file and adds it to the index.
func (g *GitBuilder) AddGen(file string) {
	g.Add(file, genString())
}

func (g *GitBuilder) lastCommitHash() string {
	return strings.TrimSpace(g.run("git", "rev-parse", "HEAD"))
}

// CommitMsg commits files in the index with the given commit message using the
// given time as the commit time. The current branch is then pushed.
// Note that the nanosecond component of time will be dropped. Returns the hash
// of the new commit.
func (g *GitBuilder) CommitMsgAt(msg string, time time.Time) string {
	g.runCommand(&exec.Command{
		Name: "git",
		Args: []string{"commit", "-m", msg},
		Env:  []string{fmt.Sprintf("GIT_AUTHOR_DATE=%d +0000", time.Unix()), fmt.Sprintf("GIT_COMMITTER_DATE=%d +0000", time.Unix())},
	})
	g.push()
	return g.lastCommitHash()
}

// CommitMsg commits files in the index with the given commit message. The
// current branch is then pushed. Returns the hash of the new commit.
func (g *GitBuilder) CommitMsg(msg string) string {
	return g.CommitMsgAt(msg, time.Now())
}

// Commit commits files in the index. The current branch is then pushed. Uses an
// arbitrary commit message. Returns the hash of the new commit.
func (g *GitBuilder) Commit() string {
	return g.CommitMsg(genString())
}

// CommitGen commits arbitrary content to the given file. The current branch is
// then pushed. Returns the hash of the new commit.
func (g *GitBuilder) CommitGen(file string) string {
	s := genString()
	g.Add(file, s)
	return g.CommitMsg(s)
}

// CommitGenAt commits arbitrary content to the given file using the given time
// as the commit time. Note that the nanosecond component of time will be
// dropped. Returns the hash of the new commit.
func (g *GitBuilder) CommitGenAt(file string, ts time.Time) string {
	g.AddGen(file)
	return g.CommitMsgAt(genString(), ts)
}

// CommitGenMsg commits arbitrary content to the given file and uses the given
// commit message. The current branch is then pushed. Returns the hash of the
// new commit.
func (g *GitBuilder) CommitGenMsg(file, msg string) string {
	g.AddGen(file)
	return g.CommitMsg(msg)
}

// CreateBranchTrackBranch creates a new branch tracking an existing branch,
// checks out the new branch, and pushes the new branch.
func (g *GitBuilder) CreateBranchTrackBranch(newBranch, existingBranch string) {
	g.run("git", "checkout", "-b", newBranch, "-t", existingBranch)
	g.branch = newBranch
	g.push()
}

// CreateBranchTrackBranch creates a new branch pointing at the given commit,
// checks out the new branch, and pushes the new branch.
func (g *GitBuilder) CreateBranchAtCommit(name, commit string) {
	g.run("git", "checkout", "--no-track", "-b", name, commit)
	g.branch = name
	g.push()
}

// CreateOrphanBranch creates a new orphan branch.
func (g *GitBuilder) CreateOrphanBranch(newBranch string) {
	g.run("git", "checkout", "--orphan", newBranch)
	g.branch = newBranch
	// Can't push, since the branch doesn't currently point to any commit.
}

// CheckoutBranch checks out the given branch.
func (g *GitBuilder) CheckoutBranch(name string) {
	g.run("git", "checkout", name)
	g.branch = name
}

// MergeBranch merges the given branch into the current branch and pushes the
// current branch. Returns the hash of the new commit.
func (g *GitBuilder) MergeBranch(name string) string {
	assert.NotEqual(g.t, g.branch, name, "Can't merge a branch into itself.")
	cmd := []string{"git", "merge", name}
	major, minor, err := git_common.Version()
	assert.NoError(g.t, err)
	if (major == 2 && minor >= 9) || major > 2 {
		cmd = append(cmd, "--allow-unrelated-histories")
	}
	g.run(cmd...)
	g.push()
	return g.lastCommitHash()
}

// Reset runs "git reset" in the repo.
func (g *GitBuilder) Reset(args ...string) {
	cmd := append([]string{"git", "reset"}, args...)
	g.run(cmd...)
	g.push()
}

// UpdateRef runs "git update-ref" in the repo.
func (g *GitBuilder) UpdateRef(args ...string) {
	cmd := append([]string{"git", "update-ref"}, args...)
	g.run(cmd...)
	g.push()
}

// CreateFakeGerritCLGen creates a Gerrit-like ref so that it can be applied like
// a CL on a trybot.
func (g *GitBuilder) CreateFakeGerritCLGen(issue, patchset string) {
	currentBranch := strings.TrimSpace(g.run("git", "rev-parse", "--abbrev-ref", "HEAD"))
	g.CreateBranchTrackBranch("fake-patch", "master")
	patchCommit := g.CommitGen("somefile")
	g.UpdateRef(fmt.Sprintf("refs/changes/%s/%s/%s", issue[len(issue)-2:], issue, patchset), patchCommit)
	g.CheckoutBranch(currentBranch)
	g.run("git", "branch", "-D", "fake-patch")
}

// GitSetup adds commits to the Git repo managed by g.
//
// The repo layout looks like this:
//
// older           newer
// c0--c1------c3--c4--
//       \-c2-----/
//
// Returns the commit hashes in order from c0-c4.
func GitSetup(g *GitBuilder) []string {
	c0 := g.CommitGen("myfile.txt")
	c1 := g.CommitGen("myfile.txt")
	g.CreateBranchTrackBranch("branch2", "origin/master")
	c2 := g.CommitGen("anotherfile.txt")
	g.CheckoutBranch("master")
	c3 := g.CommitGen("myfile.txt")
	c4 := g.MergeBranch("branch2")
	return []string{c0, c1, c2, c3, c4}
}
