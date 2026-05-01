package Test03WithView {
    private import StandardViewDefinitions::*;

    part def Seq3 {
        part a {
            event occurrence e1;
        }
        part b {
            event occurrence e2;
        }
        message m1 from a.e1 to b.e2;
    }

    view seqView : SequenceView {
        expose Test03WithView::Seq3;
    }
}
