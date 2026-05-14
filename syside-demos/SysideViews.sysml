// Copyright (c) 2026 Sensmetry, UAB. All Rights Reserved.
// Version 0.9.0
library package <SV> SysideViews {
    enum def <CT> ColumnType {
        enum declaredShortName {
            doc
            /* The short name of the element as declared in the model.
             *
             * **Editing**
             *
             * This is an explicit element, but **does not** currently support editing through the UI.
             */
        }
        enum declaredName {
            doc
            /* The name of the element as declared in the model.
             *
             * **Editing**
             *
             * This is an explicit element, but **does not** currently support editing through the UI.
             */
        }
        enum reqId {
            doc
            /* Alias for the declaredShortName.
             *
             * **Editing**
             *
             * This is an explicit element, but **does not** currently support editing through the UI.
             */
        }
        enum shortName {
            doc
            /* The short name of the element after the semantic resolution.
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum name {
            doc
            /* The name of the element after the semantic resolution.
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum qualifiedName {
            doc
            /* The qualified name of the element.
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum owner {
            doc
            /* The owner of the element.
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum attributeValue {
            doc
            /* The value of the attribute that is a feature of the requirement.
             *
             * **Fields**
             *
             * `attributeName` is a required field that must be set to the name of the attribute.
             *
             * **Editing**
             *
             * This is an explicit element -> **supports** editing through the UI.
             *
             * While SysML v2 supports having unnamed attributes, for the table view a non-empty `attributeName`
             * is required as attribute is a feature that can be inherited.
             */
            attribute attributeName default null;
        }
        enum namedFeatureValue {
            doc
            /* The value of the feature that is a feature of the requirement.
             *
             * **Fields**
             *
             * `featureName` is a required field that must be set to the name of the feature.
             *
             * **Editing**
             *
             * While this is an explicit element, it **does not** currently support editing
             * through the UI for clarity reasons (because '=' is overloaded for both assignment
             * and binding in SysML, depending on the feature type).
             *
             * Similar to `attributeValue`, the table view requires non-empty `featureName` due to inheritence
             */
            attribute featureName default null;
        }
        enum documentation {
            doc
            /* The documentation of the element. It takes ALL the documentations of this element
             * and concatenates them together.
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum specificDocumentation {
            doc
            /* The named documentation of the element. It takes the documentation with the name
             * specified in the `documentationName` attribute. For nameless docs, set the `documentationName` to "".
             *
             * **Fields**
             *
             * `documentationName` is a required field that must be set to the name of the documentation.
             *
             * **Editing**
             *
             * This is an explicit element -> **supports** editing through the UI.
             */
            attribute documentationName default "";
        }
        enum heritage {
            doc
            /* The heritage of the element. It recursively checks through each element from the heritage
             * and concatenates them together. E.g. the heritage of `b`:
             * ```
             * part def A;
             * part def B :> A;
             * part b : B;
             * ```
             * will be "B, A".
             *
             * **Editing**
             *
             * This is an implicit element -> **does not** support editing through the UI.
             */
        }
        enum <CL> constraintLanguage {
            enum def <ConT> ConstraintType {
                enum plain;
                enum assumed;
                enum asserted;
                enum required;
            }
            doc
            /* The language representation of a specific named constraint, e.g.:
             *
             * require constraint named_constraint {
             * language "English" <...>
             * }
             *
             * **Fields**
             *
             * `constraintName` is a required field that must be set to the name of the constraint
             * (use "" for unnamed constraints)
             *
             * `constraintType` is a required field that must be set to the type of the constraint. Currently supported types are:
             * - `plain`: The constraint is regular constraint.
             * - `assumed`: The constraint is an assumed constraint.
             * - `asserted`: The constraint is an asserted constraint.
             * - `required`: The constraint is a required constraint.
             *
             * `constraintLanguage` is a required field that must be set to the language of the constraint.
             *
             * **Editing**
             *
             * This is an explicit element -> **supports** editing through the UI.
             *
             * Similar to `attributeValue`, the table view requires non-empty `constraintName` due to inheritence
             */
            attribute constraintName default "";
            attribute constraintType default ConstraintType::plain;
            attribute constraintLanguage default "English";
        }
    }

    enum def <Dir> MatrixTraceabilityDirection {
        enum undirected {
            doc
            /* Row can either be in source or target, and column is the other of the two.
             * Shows "✔" if relationship fits.
             */
        }
        enum row2col {
            doc
            /* Source is row, target is column. Shows "↗" if relationship fits. */
        }
        enum col2row {
            doc
            /* Source is column, target is row. Shows "↙" if relationship fits. */
        }
    }

    enum def <Rep> MatrixElementRepresentation {
        enum name;
        enum shortName;
        enum qualifiedName;
    }

    view def ContentView {
        attribute includeLibraryElements default false;
        attribute includeReferenceElements default false;
        attribute includeAbstractElements default false;
        attribute exposeFeaturesAndHeritage default false;
    }

    package <TVD> TableViewDefinitions {
        view def <TV> TableView :> ContentView {
            private import ScalarValues::*;
            attribute maxRowHeight : Integer default 125;
            ref columnOrder :> columnViews [0..*];
            view columnViews [0..*] {
                doc
                /* Subset these views to set what columns you'd like to see in your table.
                 *
                 * The order is preserved, unless overwritten in `columnOrder`
                 */
                attribute featureToRender : CT default CT::qualifiedName {
                    doc
                    /* With this attribute you can choose what aspect of the element to visualise in the column.
                     *
                     * The choices are available in the `ColumnType` enum.
                     */
                }
                attribute defaultValue default "" {
                    doc
                    /* Set what default value to show if no feature value or no documentation is found.
                     *
                     * Default is empty cell.
                     *
                     * Default Value is rendered as grayed out and in italics.
                     */
                }
                attribute columnWidth : Integer default 150;
            }
        }
    } // package <TVD> TableViewDefinitions

    package <MVD> MatrixViewDefinitions {
        view def <MV> MatrixView {
            view rowView : ContentView [1] {
                doc
                /* Inside this view use `expose` and `filter` to specify what you want to see
                 * as rows in the matrix.
                 */
                attribute representation : Rep default Rep::name;
            }
            view columnView : ContentView [1] {
                doc
                /* Inside this view use `expose` and `filter` to specify what you want to see
                 * as columns in the matrix.
                 */
                attribute representation : Rep default Rep::name;
                attribute verticalColumnNames default false;
            }
            view cellView : ContentView [1] {
                doc
                /* Inside this view use `expose`, `filter`, and `direction` to specify what you want to see
                 * as cells in the matrix.
                 */
                attribute :>> includeReferenceElements default true;
                attribute direction : Dir default Dir::undirected;
                attribute showWeakTraceability default false;
                attribute portsAreTransparent default false;
                /* If true, connections to ports will be treated as direct connections to the port's owner */
                filter (
                    as SysML::ConnectionUsage hastype SysML::ConnectionUsage or
                    as SysML::AllocationUsage hastype SysML::AllocationUsage or
                    @ RequirementDerivation::derivation
                );
            }
        }

        abstract view def EditableMatrixView :> MatrixView {
            view :>> rowView {
                filter istype SysML::Definition;
            }
            view :>> columnView {
                filter istype SysML::Definition;
            }
            view :>> cellView {
                attribute :>> exposeFeaturesAndHeritage = true;
            }
        }

        view def ConnectionMatrixView :> EditableMatrixView {
            view :>> cellView {
                filter (
                    as SysML::ConnectionUsage hastype SysML::ConnectionUsage and
                    not (@ RequirementDerivation::derivation)
                );
            }
        }

        view def AllocationMatrixView :> EditableMatrixView {
            view :>> cellView {
                filter as SysML::AllocationUsage hastype SysML::AllocationUsage;
            }
        }

        view def RequirementMatrixView :> EditableMatrixView {
            view :>> cellView {
                filter @ RequirementDerivation::derivation;
            }
        }
    } // package <MVD> MatrixViewDefinitions
} // library package <SV> SysideViews
