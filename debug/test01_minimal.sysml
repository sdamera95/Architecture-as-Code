package Test01Minimal {
    part def Seq1 {
        part a {
            event occurrence e1;
        }
        part b {
            event occurrence e2;
        }
        message m1 from a.e1 to b.e2;
    }
}
